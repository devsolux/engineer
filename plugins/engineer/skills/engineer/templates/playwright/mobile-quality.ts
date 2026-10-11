export function viewportQualityIssues(content: string | null): string[] {
  if (content === null) return ["mobile pages need a viewport declaration"];

  const properties = new Map<string, string>();
  const duplicateProperties = new Set<string>();
  for (const declaration of content.toLowerCase().split(/[;,]/)) {
    const separator = declaration.indexOf("=");
    if (separator === -1) continue;
    const name = declaration.slice(0, separator).trim();
    const value = declaration.slice(separator + 1).trim();
    if (properties.has(name)) duplicateProperties.add(name);
    properties.set(name, value);
  }

  const issues = [...duplicateProperties].map(
    (name) => `viewport property is ambiguous because it is repeated: ${name}`,
  );
  if (properties.get("width") !== "device-width") {
    issues.push("viewport must use width=device-width");
  }
  const userScalable = properties.get("user-scalable") ?? "";
  if (userScalable === "no" || /^0(?:\.0+)?$/.test(userScalable)) {
    issues.push("viewport must not disable user zoom");
  }

  const maximumScale = properties.get("maximum-scale");
  if (maximumScale !== undefined) {
    const parsedMaximumScale = maximumScale === "yes" ? 1 : Number(maximumScale);
    if (!Number.isFinite(parsedMaximumScale)) {
      issues.push("maximum-scale must be a valid number when declared");
    } else if (parsedMaximumScale >= 0 && parsedMaximumScale < 2) {
      issues.push("maximum-scale must preserve at least 200% zoom");
    }
  }

  return issues;
}
