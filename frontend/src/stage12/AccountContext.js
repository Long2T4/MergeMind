import { createContext, useContext } from 'react'

// The signed-in account ({ email, logout }), provided by Stage12Shell and
// shown in the sidebar. Null when rendered outside the shell (e.g. tests).
export const AccountContext = createContext(null)

export function useAccount() {
  return useContext(AccountContext)
}
