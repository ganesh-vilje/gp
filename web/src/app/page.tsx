/**
 * Public status-lookup page (screen-inventory.md #1, root route `/`).
 * Public, unauthenticated — no `AuthProvider` — and subject to the strict
 * first-load JS byte budget (dependency-strategy.md/tech-stack.md AD-1/C8):
 * only the lightweight `LookupIsland` is mounted here.
 */

import { LookupIsland } from "@/islands/LookupIsland";
import { S } from "@/strings/en";

export default function HomePage() {
  return (
    <>
      <noscript>{S.lookup.noscript}</noscript>
      <LookupIsland />
    </>
  );
}
