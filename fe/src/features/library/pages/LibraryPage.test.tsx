import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LibraryPage } from "./LibraryPage";

describe("LibraryPage", () => {
  it("hiển thị trạng thái rỗng bằng tiếng Việt", () => {
    render(<LibraryPage />);
    expect(screen.getByRole("heading", { name: "Thư viện" })).toBeInTheDocument();
    expect(screen.getByText("Chưa có truyện nào")).toBeInTheDocument();
  });
});
