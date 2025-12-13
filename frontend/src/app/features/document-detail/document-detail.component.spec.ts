import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { DocumentDetailComponent } from './document-detail.component';
import { DocumentDetail } from '../../core/models';

const BASE = 'http://localhost:8000';

const completedDoc: DocumentDetail = {
  document_id: 'doc123',
  filename: 'resume.pdf',
  content_type: 'application/pdf',
  size: 102400,
  uploaded_at: '2025-01-01T00:00:00Z',
  status: 'completed',
  error_message: null,
  extraction: {
    full_name: 'Jane Doe',
    email: 'jane@example.com',
    phone: '555-1234',
    location: 'NYC',
    summary: 'Experienced engineer',
    skills: ['Python', 'TypeScript'],
    experience: [{ company: 'Acme', title: 'Engineer', start: '2020', end: null, bullets: ['Built things'] }],
    education: [{ institution: 'MIT', degree: 'BS CS', year: '2018' }],
  },
};

const processingDoc: DocumentDetail = { ...completedDoc, status: 'processing', extraction: null };
const failedDoc: DocumentDetail = { ...completedDoc, status: 'failed', error_message: 'LLM timeout', extraction: null };

describe('DocumentDetailComponent', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    vi.useFakeTimers();
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [DocumentDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    // drain any pending requests (e.g., from in-flight polls after processing state)
    httpTesting.match(() => true).forEach((req) => req.flush({}));
    httpTesting.verify();
    vi.useRealTimers();
    localStorage.clear();
  });

  function createWithId(id = 'doc123') {
    const fixture = TestBed.createComponent(DocumentDetailComponent);
    fixture.componentRef.setInput('id', id);
    return fixture;
  }

  function flushFirst(doc: DocumentDetail) {
    vi.advanceTimersByTime(0); // fire timer(0, 2000) first tick
    httpTesting.expectOne(`${BASE}/api/documents/doc123`).flush(doc);
  }

  it('should create', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('loading is true before first response', () => {
    const fixture = createWithId();
    fixture.detectChanges();
    const comp = fixture.componentInstance as unknown as { loading: () => boolean };
    expect(comp.loading()).toBe(true);
    flushFirst(completedDoc);
  });

  it('renders filename in h1 for a completed document', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('h1')?.textContent).toContain('resume.pdf');
  });

  it('renders candidate full_name from extraction', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Jane Doe');
  });

  it('renders skills chips', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('Python');
    expect(text).toContain('TypeScript');
  });

  it('renders experience entries', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('Acme');
    expect(text).toContain('Engineer');
  });

  it('renders education entries', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('MIT');
    expect(text).toContain('BS CS');
  });

  it('shows Completed status badge', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Completed');
  });

  it('shows Extracting with AI message for processing document', () => {
    const fixture = createWithId();
    flushFirst(processingDoc);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Extracting with AI');
    const comp = fixture.componentInstance as unknown as { isProcessing: () => boolean };
    expect(comp.isProcessing()).toBe(true);
    fixture.destroy();
  });

  it('shows Extraction failed with error message for failed document', () => {
    const fixture = createWithId();
    flushFirst(failedDoc);
    fixture.detectChanges();
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('Extraction failed');
    expect(text).toContain('LLM timeout');
    const comp = fixture.componentInstance as unknown as { isFailed: () => boolean };
    expect(comp.isFailed()).toBe(true);
  });

  it('toggles raw JSON pre block on button click', () => {
    const fixture = createWithId();
    flushFirst(completedDoc);
    fixture.detectChanges();

    const comp = fixture.componentInstance as unknown as {
      showRawJson: { set: (v: boolean) => void; (): boolean };
    };
    expect(comp.showRawJson()).toBe(false);
    expect(fixture.nativeElement.querySelector('pre')).toBeNull();

    const toggleBtn = Array.from(
      fixture.nativeElement.querySelectorAll('button'),
    ).find((b) => (b as HTMLButtonElement).textContent?.includes('View raw JSON')) as HTMLButtonElement;
    toggleBtn.click();
    fixture.detectChanges();

    expect(comp.showRawJson()).toBe(true);
    expect(fixture.nativeElement.querySelector('pre')).not.toBeNull();
  });

  it('sets error signal when API call fails', () => {
    const fixture = createWithId();
    vi.advanceTimersByTime(0);
    httpTesting.expectOne(`${BASE}/api/documents/doc123`).flush(
      { detail: 'Not found' },
      { status: 404, statusText: 'Not Found' },
    );
    fixture.detectChanges();
    const comp = fixture.componentInstance as unknown as { error: () => string | null };
    expect(comp.error()).toBe('Not found');
  });

  it('rerun() POSTs to /rerun and restarts polling', () => {
    const fixture = createWithId();
    flushFirst(failedDoc);
    fixture.detectChanges();

    fixture.componentInstance.rerun();

    httpTesting
      .expectOne(`${BASE}/api/documents/doc123/rerun`)
      .flush({ document_id: 'doc123', job_id: 'j2', status: 'pending' });

    vi.advanceTimersByTime(0); // new polling subscription fires timer(0)
    httpTesting.expectOne(`${BASE}/api/documents/doc123`).flush(processingDoc);
    fixture.detectChanges();

    const comp = fixture.componentInstance as unknown as { isProcessing: () => boolean };
    expect(comp.isProcessing()).toBe(true);
    fixture.destroy();
  });
});
