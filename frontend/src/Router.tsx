import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { HomePage } from './pages/Home.page';

const router = createBrowserRouter(
  [
    {
      path: '/ui',
      element: <HomePage />,
    },
  ],
  { basename: '/api/plugins/ots_debugger_plugin' }
);

export function Router() {
  return <RouterProvider router={router} />;
}
