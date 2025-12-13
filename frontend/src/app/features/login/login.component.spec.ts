import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { LoginComponent } from './login.component';

const BASE = 'http://localhost:8000';

describe('LoginComponent', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
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
    localStorage.clear();
  });

  function setup() {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    return { fixture, el };
  }

  it('should create', () => {
    const { fixture } = setup();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('renders Sign in heading', () => {
    const { el } = setup();
    expect(el.querySelector('h1')?.textContent).toContain('Sign in to DocuParse');
  });

  it('shows Sign in button text when not loading', () => {
    const { el } = setup();
    const btn = el.querySelector<HTMLButtonElement>('button[type="submit"]');
    expect(btn?.textContent?.trim()).toContain('Sign in');
  });

  it('sets email signal from input event', () => {
    const { fixture, el } = setup();
    const input = el.querySelector<HTMLInputElement>('#email')!;
    input.value = 'user@test.com';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect((fixture.componentInstance as unknown as { email: () => string }).email()).toBe(
      'user@test.com',
    );
  });

  it('on successful login: navigates to /documents', () => {
    const { fixture, el } = setup();
    const routerSpy = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    const emailInput = el.querySelector<HTMLInputElement>('#email')!;
    emailInput.value = 'a@b.com';
    emailInput.dispatchEvent(new Event('input'));
    const passwordInput = el.querySelector<HTMLInputElement>('#password')!;
    passwordInput.value = 'pass';
    passwordInput.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    fixture.componentInstance.submit();

    httpTesting
      .expectOne(`${BASE}/auth/login`)
      .flush({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' });
    httpTesting.expectOne(`${BASE}/auth/me`).flush({ id: '1', email: 'a@b.com' });

    expect(routerSpy).toHaveBeenCalledWith(['/documents']);
  });

  it('shows server error detail on 401', () => {
    const { fixture, el } = setup();
    fixture.componentInstance.submit();

    httpTesting
      .expectOne(`${BASE}/auth/login`)
      .flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });
    fixture.detectChanges();

    expect(el.querySelector('.text-red-700')?.textContent).toContain('Invalid credentials');
  });

  it('shows fallback message when error has no detail', () => {
    const { fixture, el } = setup();
    fixture.componentInstance.submit();

    httpTesting
      .expectOne(`${BASE}/auth/login`)
      .flush({}, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(el.querySelector('.text-red-700')?.textContent).toContain(
      'Login failed. Please try again.',
    );
  });

  it('loading signal is true while request is in-flight', () => {
    const { fixture } = setup();
    fixture.componentInstance.submit();
    fixture.detectChanges();

    const comp = fixture.componentInstance as unknown as { loading: () => boolean };
    expect(comp.loading()).toBe(true);

    // drain to avoid verify failure
    httpTesting
      .expectOne(`${BASE}/auth/login`)
      .flush({}, { status: 500, statusText: 'Error' });
  });
});
