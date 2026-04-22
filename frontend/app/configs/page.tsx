import ConfigsClient from "@/components/ConfigsClient";
import { serverApi } from "@/lib/server-api";
import type { ConfigurationComparison } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function ConfigurationsPage() {
  let configs: ConfigurationComparison[] = [];

  try {
    configs = await serverApi.getConfigurationComparison();
  } catch {
    configs = [];
  }

  return <ConfigsClient configs={configs} />;
}
