import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createSession, getSessionHistory, deleteSessionHistory, ApiError } from '../services/apiClient';
import { useTouristStore } from '../stores/touristStore';

export function useSession() {
  const queryClient = useQueryClient();
  const { sessionUuid, language, setSessionUuid } = useTouristStore();

  // Initialize session if none exists
  useEffect(() => {
    async function initSession() {
      if (!sessionUuid) {
        try {
          const res = await createSession(language);
          setSessionUuid(res.session_uuid);
        } catch (err) {
          console.error('Failed to create anonymous session:', err);
        }
      }
    }
    initSession();
  }, [sessionUuid, language, setSessionUuid]);

  // Query session history
  const historyQuery = useQuery({
    queryKey: ['sessionHistory', sessionUuid],
    queryFn: async () => {
      if (!sessionUuid) return null;
      try {
        return await getSessionHistory(sessionUuid);
      } catch (err: any) {
        if (err instanceof ApiError && err.status === 404) {
          // Session expired or deleted on backend -> re-create
          const newSession = await createSession(language);
          setSessionUuid(newSession.session_uuid);
          return {
            session_uuid: newSession.session_uuid,
            language_code: newSession.language_code,
            total_messages: 0,
            messages: [],
          };
        }
        throw err;
      }
    },
    enabled: !!sessionUuid,
    staleTime: 1000 * 60 * 5, // 5 min
  });

  // Clear history mutation
  const clearMutation = useMutation({
    mutationFn: async () => {
      if (!sessionUuid) return;
      await deleteSessionHistory(sessionUuid);
    },
    onSuccess: () => {
      queryClient.setQueryData(['sessionHistory', sessionUuid], (old: any) => {
        if (!old) return old;
        return { ...old, total_messages: 0, messages: [] };
      });
    },
  });

  return {
    sessionUuid,
    language,
    history: historyQuery.data?.messages || [],
    isLoadingHistory: historyQuery.isLoading,
    isErrorHistory: historyQuery.isError,
    clearHistory: clearMutation.mutateAsync,
    isClearing: clearMutation.isPending,
  };
}
