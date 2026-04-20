import { Suspense } from "react";

import { GraphPageClient, GraphPageLoadingPanel } from "./graph-page-client";

export const dynamic = "force-dynamic";

export default function GraphPage() {
  return (
    <Suspense fallback={<GraphPageLoadingPanel />}>
      <GraphPageClient />
    </Suspense>
  );
}
