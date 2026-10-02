import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import "@/shared/i18n";
import "@/styles/global.css";

const container = document.getElementById("root");
if (!container) throw new Error("Không tìm thấy #root");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
