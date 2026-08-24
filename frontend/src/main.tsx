import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import ErrorBoundary from "./diagnostics/ErrorBoundary";
import { installGlobalErrorHandlers } from "./diagnostics/globalHandlers";
import { installClickTracking } from "./diagnostics/tracking";

installGlobalErrorHandlers();
installClickTracking();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
