export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

/**
 * Validates and returns a safe redirect URL from the `next` query parameter.
 * Only allows same-origin paths to prevent open redirect vulnerabilities.
 * @param next - The next URL from query parameters
 * @param defaultPath - Default path if next is invalid (default: "/account")
 * @returns A safe, validated path or the default
 */
export function getNextUrl(next: string | null | undefined, defaultPath: string = "/account"): string {
  // If no next parameter, return default
  if (!next) {
    return defaultPath;
  }

  // Only allow relative paths starting with /
  // This prevents open redirects to external sites
  if (!next.startsWith("/")) {
    return defaultPath;
  }

  // Prevent protocol-relative URLs (//example.com)
  if (next.startsWith("//")) {
    return defaultPath;
  }

  // Prevent javascript: or data: URLs
  if (next.toLowerCase().startsWith("javascript:") || next.toLowerCase().startsWith("data:")) {
    return defaultPath;
  }

  return next;
}
