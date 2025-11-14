import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Thai Song Era Classifier",
  description: "Paste Thai lyrics and predict musical era."
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
