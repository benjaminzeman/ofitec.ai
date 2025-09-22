'use client';
import EPClient from './EPClient';
import { useParams } from 'next/navigation';

export default function Page() {
  const params = useParams() as { project?: string };
  const project = decodeURIComponent(params?.project || '');
  return <EPClient projectKey={project} />;
}
