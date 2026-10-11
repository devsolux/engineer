/**
 * Flat ESLint config snippet for Next.js App Router + TypeScript.
 * Copy to the app repo as eslint.config.mjs and adjust paths.
 *
 * Requires (typical):
 * eslint, eslint-config-next, typescript-eslint, eslint-plugin-jsx-a11y
 *
 * Pair with CI: eslint . --max-warnings=0
 * See references/enforcement.md + references/enforcement-rules.md
 */
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";
import jsxA11y from "eslint-plugin-jsx-a11y";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
 baseDirectory: __dirname,
});

/** @type {import("eslint").Linter.Config[]} */
const config = [
 ...compat.extends("next/core-web-vitals", "next/typescript"),
 {
 ignores: [
 ".next/**",
 "node_modules/**",
 "coverage/**",
 "playwright-report/**",
 "supabase/functions/**",
 ],
 },
 {
 rules: {
 // Prefer explicit deps in effects for agent-generated code
 "react-hooks/exhaustive-deps": "warn",
 // Keep noise down in generated UI; tighten in mature apps
 "@typescript-eslint/no-unused-vars": [
 "warn",
 { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
 ],
 },
 },
 // engineer enforcement baseline (references/enforcement-rules.md)
 {
 rules: {
 // a11y - escalate warnings to errors in CI
 ...jsxA11y.flatConfigs.recommended.rules,
 "jsx-a11y/label-has-associated-control": "error",
 "jsx-a11y/no-autofocus": "warn",

 // TypeScript
 "@typescript-eslint/no-explicit-any": "error",

 // Security-ish
 "no-restricted-imports": ["error", {
 paths: [{
 name: "@/lib/supabase/admin",
 message: "Admin client is server-only. Use createClient from server.ts.",
 }],
 }],
 },
 },
 {
 files: ["app/**/layout.tsx", "app/layout.tsx"],
 rules: {
 "no-restricted-syntax": ["error", {
 selector: "Program > ExpressionStatement[directive='use client']",
 message: "Do not use 'use client' on layouts - push boundary down.",
 }],
 },
 },
];

export default config;
