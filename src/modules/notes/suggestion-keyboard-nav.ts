/**
 * Shared ArrowUp/Down/Enter navigation for a Tiptap Suggestion popup.
 *
 * @tiptap/suggestion's `onKeyDown` hook only sees keys the extension chooses
 * to handle — by default both SlashCommandExtension and WikiLinkExtension
 * handled Escape only, so ArrowDown/ArrowUp/Enter fell through to
 * ProseMirror's default handling (moving the cursor / inserting a newline —
 * R15-UI-024 repro b). Both extensions need identical navigation, so it is
 * factored out once here rather than duplicated.
 */
export function createKeyboardNav<T>() {
  let activeIndex = 0;
  let items: T[] = [];

  return {
    /** Call on a fresh menu open (`onStart`) to clear any stale index. */
    reset() {
      activeIndex = 0;
    },
    setItems(next: T[]) {
      items = next;
      if (activeIndex >= items.length) activeIndex = Math.max(items.length - 1, 0);
    },
    getItems(): T[] {
      return items;
    },
    get activeIndex(): number {
      return activeIndex;
    },
    setActiveIndex(index: number) {
      if (items.length === 0) return;
      activeIndex = ((index % items.length) + items.length) % items.length;
    },
    /**
     * Handles ArrowUp/ArrowDown/Enter. Returns true when the key was
     * consumed — the caller must then return true from `onKeyDown` so
     * ProseMirror does not also apply its own default handling for the key.
     */
    handleKey(key: string, onSelect: (item: T) => void): boolean {
      if (items.length === 0) return false;
      if (key === "ArrowDown") {
        this.setActiveIndex(activeIndex + 1);
        return true;
      }
      if (key === "ArrowUp") {
        this.setActiveIndex(activeIndex - 1);
        return true;
      }
      if (key === "Enter") {
        onSelect(items[activeIndex]);
        return true;
      }
      return false;
    },
  };
}
