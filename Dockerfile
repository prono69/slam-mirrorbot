FROM breakdowns/mega-sdk-python:latest
 

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY .netrc /root/.netrc
RUN chmod 600 /usr/src/app/.netrc
RUN chmod +x aria.sh
 
CMD ["bash","start.sh"]