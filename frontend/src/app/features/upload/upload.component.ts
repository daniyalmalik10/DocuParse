import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { HttpErrorResponse, HttpEventType } from '@angular/common/http';
import { ApiService } from '../../core/api.service';

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_BYTES = 5 * 1024 * 1024;

@Component({
  selector: 'app-upload',
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
})
export class UploadComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  protected readonly dragOver = signal(false);
  protected readonly file = signal<File | null>(null);
  protected readonly validationError = signal<string | null>(null);
  protected readonly uploadProgress = signal<number | null>(null);
  protected readonly serverError = signal<string | null>(null);
  protected readonly uploading = signal(false);

  protected readonly fileSizeLabel = computed(() => {
    const f = this.file();
    if (!f) return null;
    return f.size < 1024 * 1024
      ? `${(f.size / 1024).toFixed(1)} KB`
      : `${(f.size / (1024 * 1024)).toFixed(2)} MB`;
  });

  protected readonly canUpload = computed(
    () => this.file() !== null && this.validationError() === null && !this.uploading(),
  );

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    this.selectFile(event.dataTransfer?.files[0] ?? null);
  }

  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectFile(input.files?.[0] ?? null);
    input.value = '';
  }

  private selectFile(f: File | null): void {
    this.serverError.set(null);
    this.uploadProgress.set(null);
    this.file.set(f);

    if (!f) {
      this.validationError.set(null);
      return;
    }
    if (!ACCEPTED_TYPES.includes(f.type)) {
      this.validationError.set('Only PDF and DOCX files are accepted.');
      return;
    }
    if (f.size > MAX_BYTES) {
      this.validationError.set(
        `File exceeds the 5 MB limit (${(f.size / (1024 * 1024)).toFixed(2)} MB).`,
      );
      return;
    }
    this.validationError.set(null);
  }

  upload(): void {
    const f = this.file();
    if (!f || !this.canUpload()) return;

    this.uploading.set(true);
    this.serverError.set(null);
    this.uploadProgress.set(0);

    this.api.uploadDocument(f).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          const total = event.total ?? f.size;
          this.uploadProgress.set(Math.round((event.loaded / total) * 100));
        } else if (event.type === HttpEventType.Response && event.body) {
          this.uploading.set(false);
          this.router.navigate(['/documents', event.body.document_id]);
        }
      },
      error: (err: unknown) => {
        this.uploading.set(false);
        this.uploadProgress.set(null);
        if (err instanceof HttpErrorResponse) {
          const detail = (err.error as { detail?: string } | null)?.detail;
          this.serverError.set(detail ?? `Server error: ${err.status}`);
        } else {
          this.serverError.set('Upload failed. Please try again.');
        }
      },
    });
  }
}
