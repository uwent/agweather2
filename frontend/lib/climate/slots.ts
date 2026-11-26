// The Climate tab's sections each take 1–4 s of the server's time (track 6.2), so they queue for two slots
// (lib/slots.ts) rather than all asking at once.

import { slots } from '../slots'

export { slots, type Slots } from '../slots'

/** The climate sections' two slots, shared by every section on the page */
export const climateSlots = slots(2)
