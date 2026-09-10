import type { Metadata } from "next";
import type { ReactNode } from "react";
import "../styles/app.css";

export const metadata: Metadata = {
  title: "Panchayat Complaint Tracker",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
