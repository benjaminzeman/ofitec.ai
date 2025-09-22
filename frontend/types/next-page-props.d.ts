// Temporary override to relax PageProps constraint expecting params as Promise.
// This allows using object params in client components until upstream config adjusted.

declare interface PageProps {
  params?: any;
  searchParams?: any;
}
