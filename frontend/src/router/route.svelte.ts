import { normalizeRoomCode } from "@/shared/roomCode";

type Destination = string | { name: string; params?: { roomCode?: string } };
const route = $state({ name: "home", params: {} as Record<string, string> });

function readLocation() {
  let match = /^\/rooms\/([^/]+)\/?$/.exec(window.location.pathname);
  let roomCode = "";
  if (match) {
    try {
      roomCode = normalizeRoomCode(decodeURIComponent(match[1]!));
    } catch {
      match = null;
    }
  }
  if (match) {
    route.name = "room";
    route.params = { roomCode };
    const path = `/rooms/${encodeURIComponent(roomCode)}`;
    if (window.location.pathname !== path) window.history.replaceState(null, "", path);
  } else {
    route.name = window.location.pathname === "/__ds" ? "design-system" : "home";
    route.params = {};
    if (route.name === "home" && window.location.pathname !== "/") window.history.replaceState(null, "", "/");
  }
}

function pathFor(destination: Destination): string {
  if (typeof destination === "string") return destination;
  if (destination.name === "room")
    return `/rooms/${encodeURIComponent(normalizeRoomCode(destination.params?.roomCode ?? ""))}`;
  return destination.name === "design-system" ? "/__ds" : "/";
}

export function startRouter() {
  readLocation();
  window.addEventListener("popstate", readLocation);
  return () => window.removeEventListener("popstate", readLocation);
}

const router = {
  push(destination: Destination) {
    window.history.pushState(null, "", pathFor(destination));
    readLocation();
    return Promise.resolve();
  },
  replace(destination: Destination) {
    window.history.replaceState(null, "", pathFor(destination));
    readLocation();
    return Promise.resolve();
  },
  currentRoute: route,
};
export function useRoute() {
  return route;
}
export function useRouter() {
  return router;
}
export default router;
