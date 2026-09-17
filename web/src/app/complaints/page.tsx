import type { Metadata } from "next";
import { ComplaintsApp } from "@/islands/ComplaintsApp";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Complaints",
};

export default function ComplaintsPage() {
  return (
    <AuthProvider>
      <ComplaintsApp />
    </AuthProvider>
  );
}
