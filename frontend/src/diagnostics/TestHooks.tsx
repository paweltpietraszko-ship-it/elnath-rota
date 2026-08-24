// ROTA-T021c section 5/6: deterministic triggers for the acceptance
// matrix's five failure classes plus an inert control and an explicit
// no-op, so Playwright can produce each diagnostic event kind without
// depending on flaky real-world timing or a real backend outage.
//
// Not a screen: no nav entry, unreachable from any real navigation
// path, rendered only when __E2E_TEST_HOOKS__ is true -- set only by
// Playwright's own webServer, never by an ordinary `npm run dev` or a
// production build (R1-4, round-1 audit: import.meta.env.DEV alone was
// also true for ordinary dev use, which is the runtime this project is
// actually operated through). Never part of what a coordinator sees.
import { useState, type CSSProperties } from "react";
import { consumePendingActionId, recordNoop } from "./tracking";

// No width/height/overflow clamp: clipping a container smaller than its
// buttons makes their real hit-test area fall outside the clip, so a
// real click lands on whatever is underneath instead of the button.
// Low opacity plus a max z-index keeps it out of a coordinator's way
// without breaking hit-testing.
const hiddenStyle: CSSProperties = {
  position: "fixed",
  bottom: 0,
  right: 0,
  opacity: 0.02,
  zIndex: 2147483647,
};

function Bomb(): never {
  throw new Error("diag-test render crash");
}

export default function TestHooks() {
  const [crash, setCrash] = useState(false);

  if (crash) return <Bomb />;

  return (
    <div data-testid="diag-test-hooks" style={hiddenStyle}>
      <button data-diag-action="diag-test-render-crash" onClick={() => setCrash(true)}>
        crash
      </button>
      <button
        data-diag-action="diag-test-unhandled-error"
        onClick={() =>
          setTimeout(() => {
            throw new Error("diag-test unhandled error");
          }, 0)
        }
      >
        unhandled-error
      </button>
      <button
        data-diag-action="diag-test-unhandled-rejection"
        onClick={() => {
          void Promise.reject(new Error("diag-test unhandled rejection"));
        }}
      >
        unhandled-rejection
      </button>
      <button data-diag-action="diag-test-inert">inert</button>
      <button
        data-diag-action="diag-test-explicit-noop"
        onClick={() => {
          const actionId = consumePendingActionId();
          if (actionId) recordNoop(actionId, "diag-test-explicit-noop");
        }}
      >
        noop
      </button>
    </div>
  );
}
