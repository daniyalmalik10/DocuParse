import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { LayoutComponent } from './shared/layout/layout.component';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'documents',
        loadComponent: () =>
          import('./features/documents-list/documents-list.component').then(
            (m) => m.DocumentsListComponent,
          ),
      },
      {
        path: 'documents/:id',
        loadComponent: () =>
          import('./features/document-detail/document-detail.component').then(
            (m) => m.DocumentDetailComponent,
          ),
      },
      {
        path: 'upload',
        loadComponent: () =>
          import('./features/upload/upload.component').then((m) => m.UploadComponent),
      },
      { path: '', redirectTo: 'documents', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: '/documents' },
];
