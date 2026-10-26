import { Suspense } from "react";
import { BenchPage } from "@/components/bench/BenchPage";

// Next 16 + cacheComponents (node_modules/next/dist/docs/01-app/02-guides/
// migrating-to-cache-components.md, "Await params inside <Suspense>"): `params` is a Promise.
// Without generateStaticParams it is request-time data, so it is awaited inside a Suspense
// boundary and the static shell (the fallback) can still prerender.
export default function Page({ params }: PageProps<"/match/[id]/bench">) {
  return (
    <Suspense fallback={<div className="m-auto text-sm text-[var(--muted)]">Loading assistant coach…</div>}>
      <Bench params={params} />
    </Suspense>
  );
}

async function Bench({ params }: Pick<PageProps<"/match/[id]/bench">, "params">) {
  const { id } = await params;
  return <BenchPage matchId={id} />;
}
