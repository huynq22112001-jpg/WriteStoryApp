import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

import { ApiError } from "@/shared/api/errors";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Chỉ thử lại lỗi mà hợp đồng lỗi đánh dấu retryable (Plan §23.1.D).
        retry: (failureCount, error) =>
          failureCount < 2 && (!(error instanceof ApiError) || error.retryable),
        refetchOnWindowFocus: false,
      },
    },
  });
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
