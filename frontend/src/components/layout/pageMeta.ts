import { createContext, useContext } from 'react';

export interface PageMeta {
  pageTitle?: string;
  pageSubtitle?: string;
  /** Which nav entry to mark current; also the key the content transition uses. */
  activePath?: string;
}

export interface PageMetaContextValue {
  meta: PageMeta;
  setMeta: (meta: PageMeta) => void;
}

/**
 * Lets a page tell the persistent shell what to put in the topbar.
 *
 * The shell outlives every page now, so a page can no longer pass its title
 * down as a prop — it publishes it here instead, and the shell reads it.
 */
export const PageMetaContext = createContext<PageMetaContextValue | null>(null);

export function usePageMeta(): PageMetaContextValue {
  const context = useContext(PageMetaContext);
  if (!context) {
    throw new Error('usePageMeta must be used within an AppLayout');
  }
  return context;
}
