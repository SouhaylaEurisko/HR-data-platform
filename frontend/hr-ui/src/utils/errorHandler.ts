/**
 * Utility function to extract user-friendly error messages from API errors.
 * Handles both Axios errors and validation errors from FastAPI.
 */
export function getErrorMessage(error: any): string {
    // Check if it's an Axios error with a response
    if (error?.response?.data) {
      const data = error.response.data;
  
      // FastAPI returns { detail: "message" } for single errors
      if (data.detail) {
        return data.detail;
      }
  
      // FastAPI validation errors return an array of errors
      if (Array.isArray(data)) {
        const firstError = data[0];
        if (firstError?.msg) {
          return firstError.msg;
        }
        if (firstError?.message) {
          return firstError.message;
        }
      }
  
      // Some APIs return { message: "..." }
      if (data.message) {
        return data.message;
      }
    }
  
    // Fallback to error message if available
    if (error?.message) {
      return error.message;
    }
  
    // Generic fallback
    return 'An unexpected error occurred. Please try again.';
  }