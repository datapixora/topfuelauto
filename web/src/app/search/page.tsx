import { Suspense } from "react";
import SearchClient from "./SearchClient";

export default function SearchPage() {
  return (
    <Suspense fallback={<div>Loading…</div>}>
      <SearchClient />
    </Suspense>
  );
}
