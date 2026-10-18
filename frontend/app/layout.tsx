import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/i18n/LanguageContext";
import { AuthProvider } from "@/lib/auth-context";
import { AppLayout } from "@/components/AppLayout";

export const metadata: Metadata = {
  title: "InfraDoc Generator - IT Infrastructure Documentation",
  description: "Plateforme de documentation technique d'infrastructure IT, HLD/LLD et dossier de mise en service.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="antialiased selection:bg-blue-100 selection:text-blue-900">
        <LanguageProvider>
          <AuthProvider>
            <AppLayout>{children}</AppLayout>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
