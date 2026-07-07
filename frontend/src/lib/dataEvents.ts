/**
 * dataEvents — lightweight pub/sub event bus for cross-component data invalidation.
 *
 * Why: The app uses standalone useState+useCallback hooks (no React Query).
 * When Gemini creates a journal entry or a journal status changes,
 * other pages (Dashboard, Reports) need to know to refetch.
 *
 * Events:
 *   'journal:created'  — a new draft journal entry was created (manual or Gemini)
 *   'journal:mutated'  — a journal entry was posted/reviewed/voided/reversed
 *
 * Usage:
 *   import { dataEvents } from '../lib/dataEvents';
 *   // Subscribe (in useEffect):
 *   const unsub = dataEvents.on('journal:mutated', () => refetch());
 *   return () => unsub();
 *   // Publish:
 *   dataEvents.emit('journal:created');
 */

type DataEventType = 'journal:created' | 'journal:mutated';
type Listener = () => void;

class DataEventBus {
  private listeners = new Map<DataEventType, Set<Listener>>();

  on(event: DataEventType, listener: Listener): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);
    return () => {
      this.listeners.get(event)?.delete(listener);
    };
  }

  emit(event: DataEventType): void {
    this.listeners.get(event)?.forEach((fn) => {
      try {
        fn();
      } catch {
        // Don't let a listener failure break the event chain
      }
    });
  }
}

export const dataEvents = new DataEventBus();
