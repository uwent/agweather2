// Words shared by the pages' prose: a count with its noun

/** "1 day", "3 days"; `many` for a plural that isn't the singular plus "s" */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`
}
