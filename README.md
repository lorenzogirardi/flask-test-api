# python rest api test application

Working most of the times (always) in Platform i'm usually play with the infrastructure, however sometimes to create prototype i need backends that are done for the specific purpose.  

## GOALS:
 - The application must be a REST api
 - Run in kubernetes
<br/><br/>
<br/><br/>
### Docker and kubernetes  
The application is working with GET, POST, PUT, DELETE  
enouth to cover most of the usages based on rest api.  

Inside the docker path you can run easly as local docker  

```docker build --tag pytbak:0.1 .```  
```docker run -t -p 5000:5000 pytbak:0.1```  
and access on it with ```locahost:5000/api/```

instead if you want to run it in kubernetes ,  
starting from the main folder you can  apply the kubernetes folder on your environment  
```kubectl apply -f kubernetes/ ```  

```
$ kubectl  get pods -n pytbak
NAME                             READY   STATUS    RESTARTS   AGE
pytbak-stable-5dfb4fbfd4-n64kx   1/1     Running   0          40m
```

Remember to change the host in the ingress file configuration  
```
$ cat 03-ing-pytbak.yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: pytbak-ingress
  namespace: pytbak
  annotations:
    ingress.kubernetes.io/proxy-connect-timeout: "10"
    ingress.kubernetes.io/proxy-read-timeout: "30"
    ingress.kubernetes.io/proxy-send-timeout: "30"
spec:
  rules:
  - host: pytbak.ing.h4x0r3d.lan
    http:
      paths:
      - path: /
        backend:
          serviceName: pytbak-svc
          servicePort: 5000
```

*host: pytbak.ing.h4x0r3d.lan* this is my ingress dns resolution

TIPS: for ingress endpoints you can manage multiple namespace creating an A record in your DNS (as a subdomain) with a wildcard dedicated only for ingress matching the namespace and the host created

in my case i have the home dns as ```h4x0r3d.lan```  
and ```*.ing.h4x0r3d.lan``` as a record A of my kubernetes ingress  
in this way if i create a namespace *pippo* the dns that i have to call to reach it out will be *pippo.ing.4x0r3d.lan* with no change on DNS.
<br/><br/>
<br/><br/>
### Usage

The application answer on /api/ with the main html page with methods  

| HTTP Method |                       URI                         | Action                     |
|-------------|:-------------------------------------------------:|----------------------------|
| GET         | http://[hostname]/api/get/context                 | Retrieve list of context   |
| GET         | http://[hostname]/api/get/context/[context_id]    | Retrieve a context         |
| POST        | http://[hostname]/api/post/context                | Create a new context       |
| PUT         | http://[hostname]/api/put/context/[context_id]    | Update an existing context |
| DELETE      | http://[hostname]/api/delete/context/[context_id] | Delete acontext            |  
| GET         | http://[hostname]/api/fib/[number]                | Generate Fibonacci         |

Following the methods example

```
$ curl -i http://pytbak.ing.h4x0r3d.lan/api/get/context
HTTP/1.1 200 OK
Server: openresty/1.15.8.1
Date: Wed, 28 Oct 2020 20:02:02 GMT
Content-Type: application/json
Content-Length: 696
Connection: keep-alive
Vary: Accept-Encoding

{
  "context": [
    {
      "description": "RHEL 6 based",
      "done": false,
      "title": "Cento 6",
      "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/1"
    },
    {
      "description": "RHEL 7 based",
      "done": false,
      "title": "Centos 7",
      "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/2"
    },
    {
      "description": "RHEL 8 based",
      "done": false,
      "title": "Centos 8",
      "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/3"
    },
    {
      "description": "Fedora + RHEL based",
      "done": false,
      "title": "Centos stream",
      "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/4"
    }
  ]
```  
<br/><br/>
```
$ curl -i -H "Content-Type: application/json" -X POST -d '{"title":"Ubuntu 20.04 LTS", "description":"focal"}' http://pytbak.ing.h4x0r3d.lan/api/post/context
HTTP/1.1 201 CREATED
Server: openresty/1.15.8.1
Date: Wed, 28 Oct 2020 19:49:31 GMT
Content-Type: application/json
Content-Length: 165
Connection: keep-alive

{
  "task": {
    "description": "focal",
    "done": false,
    "title": "Ubuntu 20.04 LTS",
    "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/5"
  }
}
```
<br/><br/>

```
$ curl -i -H "Content-Type: application/json" -X PUT -d '{"description":"Focal Fossa"}' http://pytbak.ing.h4x0r3d.lan/api/put/context/5
HTTP/1.1 200 OK
Server: openresty/1.15.8.1
Date: Wed, 28 Oct 2020 20:02:43 GMT
Content-Type: application/json
Content-Length: 171
Connection: keep-alive

{
  "task": {
    "description": "Focal Fossa",
    "done": false,
    "title": "Ubuntu 20.04 LTS",
    "uri": "http://pytbak.ing.h4x0r3d.lan/api/get/context/5"
  }
}
```
<br/><br/>

```
$ curl -i -H "Content-Type: application/json" -X DELETE http://pytbak.ing.h4x0r3d.lan/api/delete/context/5
HTTP/1.1 200 OK
Server: openresty/1.15.8.1
Date: Wed, 28 Oct 2020 20:04:47 GMT
Content-Type: application/json
Content-Length: 21
Connection: keep-alive

{
  "result": true
}
$ curl -i http://pytbak.ing.h4x0r3d.lan/api/get/context/5
HTTP/1.1 404 NOT FOUND
Server: openresty/1.15.8.1
Date: Wed, 28 Oct 2020 20:04:54 GMT
Content-Type: application/json
Content-Length: 27
Connection: keep-alive

{
  "error": "Not found"
}
```
<br/><br/>  

```
$ curl -i localhost:5000/api/fib/100
HTTP/1.0 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 21
Server: Werkzeug/2.0.3 Python/3.9.10
Date: Mon, 21 Feb 2022 15:16:32 GMT

354224848179261915075
```


<br/><br/>  

```
$ time curl localhost:5000/api/sleep/5
HTTP/1.1 200 OK
Server: Werkzeug/2.1.2 Python/3.9.13
Date: Fri, 01 Jul 2022 16:24:04 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 20
Vary: Accept-Encoding
Connection: close

delayed by 5 seconds
real	0m5.014s
user	0m0.005s
sys	0m0.005s
```


### metrics
application supports /metrics endpoint
```
$ curl localhost:5000/metrics
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 180.0
python_gc_objects_collected_total{generation="1"} 316.0
python_gc_objects_collected_total{generation="2"} 0.0
# HELP python_gc_objects_uncollectable_total Uncollectable object found during GC
# TYPE python_gc_objects_uncollectable_total counter
python_gc_objects_uncollectable_total{generation="0"} 0.0
python_gc_objects_uncollectable_total{generation="1"} 0.0
python_gc_objects_uncollectable_total{generation="2"} 0.0
# HELP python_gc_collections_total Number of times this generation was collected
# TYPE python_gc_collections_total counter
python_gc_collections_total{generation="0"} 75.0
python_gc_collections_total{generation="1"} 6.0
python_gc_collections_total{generation="2"} 0.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="9",patchlevel="6",version="3.9.6"} 1.0
etc etc ...
```      

### logs

application has a log handler that write INFO in /var/log/app.log
```
$ docker exec -ti 5a6205570016 cat /var/log/app.log
2021-08-17 11:42:32,759 INFO werkzeug MainThread :  * Running on http://172.17.0.2:5000/ (Press CTRL+C to quit)
2021-08-17 11:42:45,973 INFO werkzeug Thread-1 : 172.17.0.1 - - [17/Aug/2021 11:42:45] "GET /A/ HTTP/1.1" 200 -
2021-08-17 11:42:55,778 INFO werkzeug Thread-2 : 172.17.0.1 - - [17/Aug/2021 11:42:55] "GET /A/get/context HTTP/1.1" 200 -
2021-08-17 11:43:13,769 INFO werkzeug Thread-3 : 172.17.0.1 - - [17/Aug/2021 11:43:13] "GET /A/get/context HTTP/1.1" 200 -
2021-08-17 11:43:44,240 INFO werkzeug Thread-4 : 172.17.0.1 - - [17/Aug/2021 11:43:44] "GET /A/get/context/1 HTTP/1.1" 200 -
2021-08-17 11:48:51,725 INFO werkzeug Thread-5 : 172.17.0.1 - - [17/Aug/2021 11:48:51] "GET /metrics HTTP/1.1" 200 -
2021-08-17 11:49:08,889 INFO werkzeug Thread-6 : 172.17.0.1 - - [17/Aug/2021 11:49:08] "GET /metrics HTTP/1.1" 200 -
2021-08-17 11:49:30,101 INFO werkzeug Thread-7 : 172.17.0.1 - - [17/Aug/2021 11:49:30] "GET /metrics HTTP/1.1" 200 -
2021-08-17 11:49:41,133 INFO werkzeug Thread-8 : 172.17.0.1 - - [17/Aug/2021 11:49:41] "GET /metrics HTTP/1.1" 200 -
2021-08-17 11:51:52,795 INFO werkzeug Thread-9 : 172.17.0.1 - - [17/Aug/2021 11:51:52] "GET /A/get/context/error HTTP/1.1" 404 -
2021-08-17 11:51:57,628 INFO werkzeug Thread-10 : 172.17.0.1 - - [17/Aug/2021 11:51:57] "GET /A/get/context/nocontext HTTP/1.1" 404 -  
```
