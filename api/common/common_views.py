import os
from rest_framework.views import APIView
from rest_framework.response import Response
from mulearnbackend.settings import BASE_DIR
from django.http import StreamingHttpResponse

class CommonAPI(APIView):
    def get(self, request,log_type):
        print("log type", log_type)
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)

        if os.path.exists(log_file_path):
            try:
                def file_iterator(file_path):
                    with open(file_path, 'rb') as log_file:
                        chunk_size = 8192
                        while True:
                            chunk = log_file.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk

                response = StreamingHttpResponse(file_iterator(log_file_path), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{log_type}.log"'
                return response
            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})

class ViewCommonAPI(APIView):
    def get(self, request, log_type):
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)

        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r') as log_file:
                    log_content = log_file.read()
                
                # You can return the log content as plain text or JSON, depending on your requirements.
                # For plain text response:
                return Response({'log_content': log_content}, content_type='text/plain')

                # For JSON response:
                # return Response({'log_content': log_content})

            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})

class ClearCommonAPI(APIView):
   def post(self,request,log_type):
        log_file_path = os.path.join(BASE_DIR, 'logs', f'{log_type}.log')
        print("log file path", log_file_path)
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'w') as log_file:
                    log_file.truncate(0)
                
                return Response({'detail': f'{log_type} log cleared successfully'})

            except Exception as e:
                return Response({'detail': f'Error reading log file: {str(e)}'})
        else:
            return Response({'detail': f'{log_type} log file not found'})