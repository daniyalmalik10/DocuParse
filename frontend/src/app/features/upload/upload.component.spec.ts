import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { UploadComponent } from './upload.component';

function makeFile(name: string, type: string, sizeBytes: number): File {
  return new File([new ArrayBuffer(sizeBytes)], name, { type });
}

function mockDrop(file: File): DragEvent {
  return {
    preventDefault: () => undefined,
    dataTransfer: { files: [file] },
  } as unknown as DragEvent;
}

describe('UploadComponent', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function setup() {
    const fixture = TestBed.createComponent(UploadComponent);
    fixture.detectChanges();
    const comp = fixture.componentInstance as unknown as {
      file: () => File | null;
      validationError: () => string | null;
      canUpload: () => boolean;
      serverError: () => string | null;
    };
    return { fixture, el: fixture.nativeElement as HTMLElement, comp };
  }

  it('should create', () => {
    const { fixture } = setup();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('valid PDF is accepted with no validation error', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('resume.pdf', 'application/pdf', 1024)));
    fixture.detectChanges();
    expect(comp.validationError()).toBeNull();
    expect(comp.file()?.name).toBe('resume.pdf');
  });

  it('valid DOCX is accepted', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(
      mockDrop(
        makeFile(
          'resume.docx',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          2048,
        ),
      ),
    );
    fixture.detectChanges();
    expect(comp.validationError()).toBeNull();
  });

  it('invalid MIME type sets validation error', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('resume.txt', 'text/plain', 1024)));
    fixture.detectChanges();
    expect(comp.validationError()).toBe('Only PDF and DOCX files are accepted.');
  });

  it('file over 5 MB sets validation error', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(
      mockDrop(makeFile('big.pdf', 'application/pdf', 6 * 1024 * 1024)),
    );
    fixture.detectChanges();
    expect(comp.validationError()).toContain('File exceeds the 5 MB limit');
  });

  it('canUpload is false when no file is selected', () => {
    const { comp } = setup();
    expect(comp.canUpload()).toBe(false);
  });

  it('canUpload is false when validation error is set', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('bad.exe', 'application/octet-stream', 1024)));
    fixture.detectChanges();
    expect(comp.canUpload()).toBe(false);
  });

  it('canUpload is true for a valid file not yet uploading', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('cv.pdf', 'application/pdf', 1024)));
    fixture.detectChanges();
    expect(comp.canUpload()).toBe(true);
  });

  it('displays file name after a valid file is dropped', () => {
    const { fixture, el } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('cv.pdf', 'application/pdf', 512 * 1024)));
    fixture.detectChanges();
    expect(el.textContent).toContain('cv.pdf');
  });

  it('upload() POSTs the file and navigates to /documents/:id on success', () => {
    const routerSpy = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const { fixture } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('cv.pdf', 'application/pdf', 1024)));
    fixture.detectChanges();

    fixture.componentInstance.upload();

    httpTesting
      .expectOne((r) => r.url.includes('/api/documents/upload'))
      .flush({ document_id: 'abc123', job_id: 'j1', status: 'pending' });

    expect(routerSpy).toHaveBeenCalledWith(['/documents', 'abc123']);
  });

  it('upload() on server error sets serverError signal', () => {
    const { fixture, comp } = setup();
    fixture.componentInstance.onDrop(mockDrop(makeFile('cv.pdf', 'application/pdf', 1024)));
    fixture.detectChanges();

    fixture.componentInstance.upload();

    httpTesting
      .expectOne((r) => r.url.includes('/api/documents/upload'))
      .flush(
        { detail: 'Unsupported format' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
    fixture.detectChanges();

    expect(comp.serverError()).toContain('Unsupported format');
  });
});
