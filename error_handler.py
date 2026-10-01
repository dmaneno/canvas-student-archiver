# code based on https://github.com/davekats/canvas-student-data-export/blob/master/export.py

from canvasapi.exceptions import ResourceDoesNotExist, Unauthorized, Forbidden, InvalidAccessToken, CanvasException
import sys

# NOTE: You can see how the exceptions are raised in canvasapi.requester

# Canvas API Error Handling Utility
class CanvasErrorHandler:

    @staticmethod
    def handle_exception(e, operation_description="operation") -> dict:
        """
        Main handler function called by other modules
        """
        print(f"## Exception <{type(e).__name__}>: {str(e)}")
        
        error_type, message = CanvasErrorHandler.handle_canvas_exception(
            e, operation_description
        )
        if CanvasErrorHandler.is_fatal_error(error_type):
            print(f"FATAL: {message}")
            sys.exit(1)
        else:
            CanvasErrorHandler.log_error(error_type, message, verbose=True)

        return {"exception": f'{type(e).__name__}: {str(e)}'}


    @staticmethod
    def handle_canvas_exception(e, operation_description="operation"):
        """
        Handle Canvas API exceptions with appropriate messaging and classification.
        Returns (error_type, message)
        """
        if isinstance(e, InvalidAccessToken):
            return "authentication", f"Invalid Canvas API token during {operation_description}. Please check your credentials.yaml file."
        
        elif isinstance(e, Unauthorized):
            # Check if this is a known student limitation
            if "submissions" in operation_description.lower():
                return "student_limitation", f"Not authorized to download every student's assignment submission ({operation_description}). This is normal for student accounts."
            elif "file" in operation_description.lower():
                return "student_limitation", f"Not authorized to download some course files ({operation_description}). This is normal for student accounts."
            else:
                return "authorization", f"Not authorized to perform {operation_description}. Check your Canvas permissions."
        
        elif isinstance(e, Forbidden):
            return "student_limitation", f"Access forbidden for {operation_description}. This may be normal for student accounts."
        
        elif isinstance(e, ResourceDoesNotExist):
            return "not_found", f"Resource not found for {operation_description}. It may have been deleted or moved."
        
        elif isinstance(e, CanvasException):
            return "canvas_error", f"Canvas API error during {operation_description}: {str(e)}"
        
        else:
            return "unknown_error", f"Unexpected error during {operation_description}: {str(e)}"
    
    @staticmethod
    def log_error(error_type, message, show_details=True, verbose=False):
        """Log error messages with appropriate formatting"""
        if error_type == "student_limitation":
            if show_details:
                print(f"    Note: {message}")
        elif error_type == "not_found":
            print(f"    Skipping: {message}")
        elif error_type in ["authentication", "authorization", "canvas_error", "unknown_error"]:
            print(f"    ERROR: {message}")
            if verbose:
                import traceback
                traceback.print_exc()
        else:
            print(f"    {message}")
            
    @staticmethod
    def is_fatal_error(error_type):
        """Check if an error type should stop execution"""
        return error_type in ["authentication", "canvas_error", "authorization"]