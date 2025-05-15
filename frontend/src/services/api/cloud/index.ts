import auth from './auth'
import { pluginsMarketApi } from './plugins_market'
import { presetsMarketApi } from './presets_market'
import { telemetryApi } from './telemetry'

// Auth API
export const authApi = {
  checkGitHubStars: auth.checkGitHubStars,
}

export const cloudApi = {
  auth,
  plugins: pluginsMarketApi,
  presets: presetsMarketApi,
  telemetry: telemetryApi,
}
