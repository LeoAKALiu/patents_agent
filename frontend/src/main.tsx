import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import App from "./App";
import { installTauriDesktopBridge } from "./tauriDesktopBridge";
import { createPatentAgentQueryClient } from "./lib/queryClient";

installTauriDesktopBridge();

const queryClient = createPatentAgentQueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <App />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
);