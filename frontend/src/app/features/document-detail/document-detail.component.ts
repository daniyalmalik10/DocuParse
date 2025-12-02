import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { JsonPipe } from '@angular/common';
import { Subscription, timer } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { ApiService } from '../../core/api.service';
import { DocumentDetail, JobStatus } from '../../core/models';

const TERMINAL = new Set<JobStatus>(['completed', 'failed']);

@Component({
  selector: 'app-document-detail',
  templateUrl: './document-detail.component.html',
  styleUrl: './document-detail.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, JsonPipe],
})
export class DocumentDetailComponent implements OnDestroy {
  readonly id = input.required<string>();

  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  document = signal<DocumentDetail | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  showRawJson = signal(false);
  retrying = signal(false);

  isCompleted = computed(() => this.document()?.status === 'completed');
  isProcessing = computed(
    () => this.document()?.status === 'processing' || this.document()?.status === 'pending',
  );
  isFailed = computed(() => this.document()?.status === 'failed');

  private sub: Subscription;

  constructor() {
    this.sub = this.startPolling();
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  private startPolling(): Subscription {
    return timer(0, 2000)
      .pipe(
        switchMap(() => this.api.getDocument(this.id())),
        takeWhile((doc) => !TERMINAL.has(doc.status), true),
      )
      .subscribe({
        next: (doc) => {
          this.document.set(doc);
          this.loading.set(false);
          this.retrying.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Failed to load document.');
          this.loading.set(false);
          this.retrying.set(false);
        },
      });
  }

  rerun(): void {
    this.retrying.set(true);
    this.api.rerunExtraction(this.id()).subscribe({
      next: () => {
        this.sub.unsubscribe();
        this.document.update((d) => (d ? { ...d, status: 'pending', extraction: null } : d));
        this.sub = this.startPolling();
      },
      error: () => {
        this.error.set('Failed to start re-extraction. Please try again.');
        this.retrying.set(false);
      },
    });
  }

  formatSize(bytes: number): string {
    return bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
