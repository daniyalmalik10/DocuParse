import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { ApiService } from '../../core/api.service';
import { DocumentSummary, JobStatus } from '../../core/models';

const TERMINAL = new Set<JobStatus>(['completed', 'failed']);

@Component({
  selector: 'app-documents-list',
  templateUrl: './documents-list.component.html',
  styleUrl: './documents-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
})
export class DocumentsListComponent implements OnDestroy {
  private readonly api = inject(ApiService);

  documents = signal<DocumentSummary[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  deletingId = signal<string | null>(null);

  isEmpty = computed(() => !this.loading() && this.documents().length === 0);

  private sub: Subscription;

  constructor() {
    this.sub = timer(0, 2000)
      .pipe(
        switchMap(() => this.api.listDocuments()),
        takeWhile((res) => res.items.some((d) => !TERMINAL.has(d.status)), true),
      )
      .subscribe({
        next: (res) => {
          this.documents.set(res.items);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Failed to load documents.');
          this.loading.set(false);
        },
      });
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  confirmDelete(doc: DocumentSummary): void {
    if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    this.deletingId.set(doc.document_id);
    this.api.deleteDocument(doc.document_id).subscribe({
      next: () => {
        this.documents.update((list) => list.filter((d) => d.document_id !== doc.document_id));
        this.deletingId.set(null);
      },
      error: () => {
        this.error.set('Delete failed. Please try again.');
        this.deletingId.set(null);
      },
    });
  }

  formatSize(bytes: number): string {
    return bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
}
