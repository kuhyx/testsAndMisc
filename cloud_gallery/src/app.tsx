import { useMemo } from "react";
import { createDufsClient } from "./api/dufs-client.ts";
import { Gallery } from "./components/gallery.tsx";

export function App(): React.JSX.Element {
  const client = useMemo(() => createDufsClient(), []);
  return <Gallery client={client} />;
}
