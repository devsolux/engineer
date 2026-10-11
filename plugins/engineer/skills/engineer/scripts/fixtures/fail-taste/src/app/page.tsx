import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export default function Page() {
  return (
    <div className={`${inter.className} bg-gradient-to-r from-indigo-500 to-cyan-400 shadow-[0_0_80px_rgba(99,102,241,0.45)]`}>
      <span className="rounded-full px-3 py-1 text-xs uppercase">Now in Beta</span>
      <h1>Ship faster</h1>
      <section className="border-l-4 border-violet-500 p-4">
        <span>01</span> stripe
      </section>
    </div>
  );
}
