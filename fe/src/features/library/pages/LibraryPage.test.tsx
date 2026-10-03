import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { LibraryPage } from "./LibraryPage";

describe("LibraryPage", () => {
  it("hiển thị trạng thái rỗng bằng tiếng Việt", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><LibraryPage /></QueryClientProvider>);
    expect(screen.getByRole("heading", { name: "Thư viện" })).toBeInTheDocument();
    expect(screen.getByText("Chưa có truyện nào")).toBeInTheDocument();
  });
});
