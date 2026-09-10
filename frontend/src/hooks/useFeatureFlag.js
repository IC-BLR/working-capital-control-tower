import { useState, useEffect } from "react";
import axios from "axios";
import { AR_API_BASE } from "../config";
import { toast } from "sonner";

/**
 * Hook to manage feature flags
 */
export function useFeatureFlag(flagKey) {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFlag = async () => {
      try {
        const response = await axios.get(`${AR_API_BASE}/settings`);
        setEnabled(response.data[flagKey] || false);
      } catch (error) {
        console.error(`Error fetching feature flag ${flagKey}:`, error);
        setEnabled(false);
      } finally {
        setLoading(false);
      }
    };

    fetchFlag();
  }, [flagKey]);

  const updateFlag = async (value) => {
    try {
      await axios.put(`${AR_API_BASE}/settings/${flagKey}`, null, {
        params: { value },
      });
      setEnabled(value);
      toast.success(`Feature flag updated`);
      return true;
    } catch (error) {
      console.error(`Error updating feature flag ${flagKey}:`, error);
      toast.error(`Failed to update feature flag`);
      return false;
    }
  };

  return { enabled, loading, updateFlag };
}

/**
 * Hook to get all settings
 */
export function useSettings() {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await axios.get(`${AR_API_BASE}/settings`);
        setSettings(response.data);
      } catch (error) {
        console.error("Error fetching settings:", error);
        setSettings({});
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  return { settings, loading };
}

