import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  AccessTokenResponse,
  DocumentDetail,
  DocumentListResponse,
  TokenPair,
  UploadResponse,
  User,
} from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = 'http://localhost:8000';

  register(email: string, password: string): Observable<TokenPair> {
    return this.http.post<TokenPair>(`${this.base}/auth/register`, { email, password });
  }

  login(email: string, password: string): Observable<TokenPair> {
    return this.http.post<TokenPair>(`${this.base}/auth/login`, { email, password });
  }

  refreshToken(refreshToken: string): Observable<AccessTokenResponse> {
    return this.http.post<AccessTokenResponse>(
      `${this.base}/auth/refresh`,
      {},
      { headers: { Authorization: `Bearer ${refreshToken}` } },
    );
  }

  me(): Observable<User> {
    return this.http.get<User>(`${this.base}/auth/me`);
  }

  uploadDocument(file: File): Observable<HttpEvent<UploadResponse>> {
    const form = new FormData();
    form.append('file', file);
    const req = new HttpRequest<FormData>('POST', `${this.base}/api/documents/upload`, form, {
      reportProgress: true,
    });
    return this.http.request<UploadResponse>(req);
  }

  listDocuments(): Observable<DocumentListResponse> {
    return this.http.get<DocumentListResponse>(`${this.base}/api/documents/`);
  }

  getDocument(id: string): Observable<DocumentDetail> {
    return this.http.get<DocumentDetail>(`${this.base}/api/documents/${id}`);
  }

  deleteDocument(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/api/documents/${id}`);
  }

  rerunExtraction(id: string): Observable<UploadResponse> {
    return this.http.post<UploadResponse>(`${this.base}/api/documents/${id}/rerun`, {});
  }
}
