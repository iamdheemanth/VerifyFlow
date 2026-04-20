import ConfigsClient from "@/components/ConfigsClient";
import { api } from "@/lib/api";
import type { ConfigurationComparison } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function ConfigurationsPage() {
  let configs: ConfigurationComparison[] = [];

  try {
    configs = await api.getConfigurationComparison();
  } catch {
    configs = [];
  }

  return <ConfigsClient configs={configs} />;
}
