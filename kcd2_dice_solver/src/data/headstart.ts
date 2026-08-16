/**
 * Headstart badge point leads.
 *
 * Its own module so both halves of the badge table can import it without
 * a cycle -- an earlier attempt had badgeTableGold importing it from
 * badgeTable, which left it undefined at module-init time.
 */

import type { BadgeTier } from "./badges.ts";



/**
 * Point leads granted by the Headstart badges.
 *
 * UNVERIFIED. The wiki only says "small" / "moderate" / "large".
 */
export const HEADSTART_POINTS: Readonly<Record<BadgeTier, number>> = {
  tin: 250,
  silver: 500,
  gold: 1000,
};
