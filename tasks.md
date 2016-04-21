# 1. Master reply server foundation

```gherkin
Given that I run "agentzero master --reply-address=tcp://0.0.0.0:3000"
When a **ZMQ Request** client connects to it
Then it should print the request payload sent by the minion
And it should automatically reply with the payload "{"action": "ATTACK"}"
```

# 2. Minion client foundation

```gherkin
Background:
  Given that the Master server foundation (#1) is implemented
  And that it is binding on "localhost:3000"

Feature:
  Given that I run "agentzero minion --request-address=tcp://localhost:3000 --batch-size=2"
  When the minion boots up and sends the request "{"request": "INSTRUCTIONS"}"
  Then it should receive a reply with "ATTACK"
  And it should make 2 "POST" requests to "http://httpbin.org/post"
  And then should report back to the server in the format
    '''
    {
      "minion": {
        "id": "some-uuid",
        "name": "something-random",
        "hostname": "computers-hostname"
      },
      "test_results": [
        {
          "started_at": "1448312530",
          "finished_at": "1448312532",
          "data": {"returned-from": "attack method"},
          "bytes_received": "1024",
          "target": "http://httpbin.org/post",
          "method": "POST"
          "status_code": 200
        },
        {
          "started_at": "1448312650",
          "finished_at": "1448312654",
          "data": {"returned-from": "attack method"},
          "bytes_received": "1024",
          "target": "http://httpbin.org/post",
          "method": "POST"
          "status_code": 200
        },
      ]
    }
    '''
```


# 3. Create queue foundation and scale minions

```gherkin
Given that I run "agentzero queue --router=tcp://0.0.0.0:3000 --dealer=tcp://0.0.0.0:3001 --monitor=tcp://0.0.0.0:3002"
When I run "agentzero master --reply-address=tcp://0.0.0.0:3000"
And I run "agentzero minion --request-address=tcp://0.0.0.0:3000" 2 times
Then the master should be replying to requests from both minions
```

# 4. Add new minion action/state: IDLE

```gherkin
Given that there is a master and a minion running
When the minion sends an "ASK"
And the master replies with a "{"action": "IDLE"}"
Then the minion should send the payload:
  '''
  {
    "minion": {
      "id": "some-uuid",
      "name": "something-random",
      "hostname": "computers-hostname",
      "health": {
        "cpu_percent": [
            23.0,
            4.0,
            15.0,
            5.0
        ]
      }
    },
    "test_results": []
  }
  '''
```

# 5. Create API endpoint to return list of available minions

```gherkin
Given that I run "agentzero master --reply-address=tcp://0.0.0.0:3000 --web-host=0.0.0.0 --web-port=5000"
And 2 have minions running with "agentzero minion --request-address=tcp://0.0.0.0:3000"
When I perform an HTTP GET on "http://localhost:5000/api/minions"
Then it should return a list of minions as a JSON payload:
  '''
  [
    {
      "minion": {
        "id": "some-uuid",
        "name": "foo-bar",
        "hostname": "computers-hostname",
        "health": {
          "cpu_percent": [
              23.0,
              4.0,
              15.0,
              5.0
          ]
        }
      },
    {
      "minion": {
        "id": "another-uuid",
        "name": "hello-world",
        "hostname": "computers-hostname",
        "health": {
          "cpu_percent": [
              23.0,
              4.0,
              15.0,
              5.0
          ]
        }
      },
    }
  ]
  '''
```

# 6. Create CLI option to list available minions

```gherkin
Given that I run "agentzero master --reply-address=tcp://0.0.0.0:3000 --web-host=0.0.0.0 --web-port=5000"
And 2 have minions running with "agentzero minion --request-address=tcp://0.0.0.0:3000"
And that the environment variable "AGENTZERO_API_URL" is set to "http://localhost:5000"
When I run "agentzero list"
Then it should print a list of minions
```

# 7. Create API endpoint to instruct a minion to start attacking

```gherkin
Background:
  Given that I run "agentzero master --reply-address=tcp://0.0.0.0:3000 --web-host=0.0.0.0 --web-port=5000"
  When a **ZMQ Request** client connects to it
  Then it should print the request payload sent by the minion
  And it should NOT automatically reply with the payload "{"action": "ATTACK"}"

Feature:
  Given that the environment variable "AGENTZERO_API_URL" is set to the url of the master API
  And that there is a minion named "foo-bar" running
  And that there is a minion named "hello-world" running
  When I run "agentzero attack --minions=foo-bar,hello-world"
  Then the minions should start attacking
```

# 8. Create a CLI option to instruct a minion to start attacking

```gherkin
Given that the environment variable "AGENTZERO_API_URL" is set to the url of the master API
And that there is a minion named "foo-bar" running
And that there is a minion named "hello-world" running
When I run "agentzero attack --minions=foo-bar,hello-world"
Then the minions should start attacking
```

# 9. Create support to attack strategies

```gherkin
Background:
  Given that there is a local folder named "strategies/create-api-user"
  When I write a yaml file at "strategies/create-api-user/sling.yml" with the contents:
    '''
    name: create-api-user
    description: creates random users in the client-api, emulating a mobile-based attack.
    entrypoint: client-api.py:CreateUser
    '''

  And a python file at "strategies/create-api-user/attack.py" with the contents:
    '''
    import json
    from agentzero import Strategy

    class CreateUser(Strategy):
        def generate_random_user_data(self):
            return {
                'email': 'john@doe.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_type': 'celular',
                'phone': '111-222-3344',
                'password1': 'foobar123',
                'password2': 'foobar123',
            }

        def attack(self):
            url = "http://ingress-dev.canaryis.com"
            data = self.generate_random_user_data()
            payload = json.dumps(data)
            response = self.http.post(
                url,
                body=payload,
                headers={
                    'content-type': 'application/json',
                },
                auth=('canary', 'canary'),
            )
            user_data = response.json()
            return user_data['user']

    '''

Feature:
  Given that I run "agentzero minion --name=foo-bar --request-address=tcp://localhost:3000 --batch-size=2 --strategy-path=./strategies/"
  When I run "agentzero attack --minions=foo-bar --strategy=create-api-user"
  Then the minion should generate 2 users and report back to the mothership
```

# 10. Mothership uploading strategies to a minion

```gherkin
Background:
  Given that there is a local folder named "strategies/create-api-user"
  When I write a yaml file at "strategies/create-api-user/sling.yml" with the contents:
    '''
    name: create-api-user
    description: creates random users in the client-api, emulating a mobile-based attack.
    entrypoint: client-api.py:CreateUser
    '''

  And a python file at "strategies/create-api-user/attack.py" with the contents:
    '''
    import json
    from agentzero import Strategy

    class CreateUser(Strategy):
        def generate_random_user_data(self):
            return {
                'email': 'john@doe.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_type': 'celular',
                'phone': '111-222-3344',
                'password1': 'foobar123',
                'password2': 'foobar123',
            }

        def attack(self):
            url = "http://ingress-dev.canaryis.com"
            data = self.generate_random_user_data()
            payload = json.dumps(data)
            response = self.http.post(
                url,
                body=payload,
                headers={
                    'content-type': 'application/json',
                },
                auth=('canary', 'canary'),
            )
            user_data = response.json()
            return user_data['user']

    '''

Feature:
  Given that I run "agentzero master --reply-address=tcp://0.0.0.0:3000 --web-host=0.0.0.0 --web-port=5000 --strategy-path=./strategies"
  And 2 have minions running with "agentzero minion --request-address=tcp://0.0.0.0:3000"
  When I perform an HTTP POST on "http://localhost:5000/api/minions/MINION-UUID/strategy/create-api-user"
  And one of the minions requests instructions
  Then the mothership should generate a tarball and send it over to the minion encoded as base64 in the form:
    '''
    {
      "action": "LEARN_STRATEGY",
      "tarball": "BASE64-encoded tarball binary"
    }
    '''
  And the minion will receive and unpack the strategy in its local cache
```
