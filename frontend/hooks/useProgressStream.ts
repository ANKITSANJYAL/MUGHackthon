import { useEffect, useState, useRef } from 'react';

export interface Phase {
  id: number;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  data?: Record<string, any>;
}

export interface TicketProgress {
  ticket_key: string;
  status: string;
  current_phase: number;
  phases: Phase[];
  started_at: number;
  updated_at: number;
  ticket_title?: string;
  error?: string;
}

interface ProgressEvent {
  event: 'connected' | 'ticket_started' | 'phase_update' | 'ticket_completed' | 'ticket_error' | 'keepalive' | 'initial_state';
  ticket_key?: string;
  phase_id?: number;
  status?: string;
  data?: TicketProgress | Record<string, TicketProgress>;
  error?: string;
  result?: any;
  tickets?: Record<string, TicketProgress>;
}

export function useProgressStream() {
  const [tickets, setTickets] = useState<Record<string, TicketProgress>>({});
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
    const streamUrl = `${apiUrl}/api/progress/stream`;

    console.log('📡 Connecting to progress stream:', streamUrl);

    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('✅ Connected to progress stream');
      setConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const progressEvent: ProgressEvent = JSON.parse(event.data);
        console.log('📊 Progress event:', progressEvent);

        switch (progressEvent.event) {
          case 'connected':
            console.log('🔗 Stream connection established');
            break;

          case 'initial_state':
            if (progressEvent.tickets) {
              console.log('📦 Received initial state:', Object.keys(progressEvent.tickets).length, 'tickets');
              setTickets(progressEvent.tickets);
            }
            break;

          case 'ticket_started':
            if (progressEvent.ticket_key && progressEvent.data) {
              console.log('🎬 Ticket started:', progressEvent.ticket_key);
              setTickets(prev => ({
                ...prev,
                [progressEvent.ticket_key!]: progressEvent.data as TicketProgress
              }));
            }
            break;

          case 'phase_update':
            if (progressEvent.ticket_key && progressEvent.phase_id) {
              console.log(`📍 Phase ${progressEvent.phase_id} -> ${progressEvent.status} for ${progressEvent.ticket_key}`);
              setTickets(prev => {
                const ticket = prev[progressEvent.ticket_key!];
                if (!ticket) return prev;

                const updatedPhases = ticket.phases.map(phase =>
                  phase.id === progressEvent.phase_id
                    ? { ...phase, status: progressEvent.status as Phase['status'], data: progressEvent.data }
                    : phase
                );

                return {
                  ...prev,
                  [progressEvent.ticket_key!]: {
                    ...ticket,
                    phases: updatedPhases,
                    current_phase: progressEvent.status === 'active' ? progressEvent.phase_id! : ticket.current_phase,
                    updated_at: Date.now() / 1000
                  }
                };
              });
            }
            break;

          case 'ticket_completed':
            if (progressEvent.ticket_key) {
              console.log('✅ Ticket completed:', progressEvent.ticket_key);
              setTickets(prev => {
                const ticket = prev[progressEvent.ticket_key!];
                if (!ticket) return prev;

                return {
                  ...prev,
                  [progressEvent.ticket_key!]: {
                    ...ticket,
                    status: 'COMPLETED',
                    result: progressEvent.result
                  }
                };
              });
            }
            break;

          case 'ticket_error':
            if (progressEvent.ticket_key) {
              console.error('❌ Ticket error:', progressEvent.ticket_key, progressEvent.error);
              setTickets(prev => {
                const ticket = prev[progressEvent.ticket_key!];
                if (!ticket) return prev;

                const updatedPhases = progressEvent.phase_id
                  ? ticket.phases.map(phase =>
                      phase.id === progressEvent.phase_id
                        ? { ...phase, status: 'error' as Phase['status'] }
                        : phase
                    )
                  : ticket.phases;

                return {
                  ...prev,
                  [progressEvent.ticket_key!]: {
                    ...ticket,
                    status: 'ERROR',
                    error: progressEvent.error,
                    phases: updatedPhases
                  }
                };
              });
            }
            break;

          case 'keepalive':
            // Silent keepalive
            break;

          default:
            console.log('🔔 Unknown event:', progressEvent);
        }
      } catch (error) {
        console.error('❌ Failed to parse progress event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('❌ EventSource error:', error);
      setConnected(false);
    };

    return () => {
      console.log('🔌 Disconnecting from progress stream');
      eventSource.close();
    };
  }, []);

  return { tickets, connected };
}
