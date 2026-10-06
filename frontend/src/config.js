// Dual API bases + Working Capital spine

export const API_BASE_DEV = "http://localhost:8064/api";
export const API_BASE_PROD = "https://cct-api.indiainnovationcentre.com/api";

export const AR_API_BASE =
  process.env.REACT_APP_AR_API_BASE || API_BASE_PROD + "/ar";

export const AP_API_BASE =
  process.env.REACT_APP_AP_API_BASE || API_BASE_PROD + "/ap";

export const WC_API_BASE =
  process.env.REACT_APP_WC_API_BASE || API_BASE_PROD + "/wc";


