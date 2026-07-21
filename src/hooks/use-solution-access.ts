"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

import {
  parseSolutionAccess,
  SOLUTION_ACCESS_EVENT,
  solutionAccessKey,
  type SolutionScope,
  type StoredSolutionAccess,
} from "@/lib/solution-access";

const subscribeToBrowser = () => () => {};
const browserSnapshot = () => true;
const serverSnapshot = () => false;

export function useSolutionAccess(scope: SolutionScope): {
  access: StoredSolutionAccess | null;
  isBrowser: boolean;
} {
  const key = solutionAccessKey(scope);
  const isBrowser = useSyncExternalStore(
    subscribeToBrowser,
    browserSnapshot,
    serverSnapshot,
  );

  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const handleStorage = (event: StorageEvent) => {
        if (event.storageArea === window.sessionStorage && event.key === key) {
          onStoreChange();
        }
      };
      const handleLocalChange = (event: Event) => {
        if (event instanceof CustomEvent && event.detail === key) {
          onStoreChange();
        }
      };
      window.addEventListener("storage", handleStorage);
      window.addEventListener(SOLUTION_ACCESS_EVENT, handleLocalChange);
      return () => {
        window.removeEventListener("storage", handleStorage);
        window.removeEventListener(SOLUTION_ACCESS_EVENT, handleLocalChange);
      };
    },
    [key],
  );
  const getSnapshot = useCallback(
    () => window.sessionStorage.getItem(key),
    [key],
  );
  const rawAccess = useSyncExternalStore(subscribe, getSnapshot, () => null);
  const access = useMemo(() => parseSolutionAccess(rawAccess), [rawAccess]);

  return { access, isBrowser };
}
