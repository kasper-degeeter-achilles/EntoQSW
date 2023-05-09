#include <Controllino.h> /* Usage of CONTROLLINO library allows you to use CONTROLLINO_xx aliases in your sketch.*/ 
#include <ArduinoJson.h>

#define PC_MSG_MAXLENGTH 512
#define DEBUG 1
#define SERIALSPEED 115200
#define TERMINATOR 0x00

#if DEBUG == 1
#define debug(x) Serial2.print(x)
#define debugln(x) Serial2.println(x)
#else
#define debug(x)
#define debugln(x)
#endif

#define JSON_MSGID_MSG_ERROR "msg_error"
#define JSON_MSGID_FIRE "fire"


int capSensor=CONTROLLINO_I16;
int synchPin=CONTROLLINO_D0;
int relay0=CONTROLLINO_R0;
int relay1=CONTROLLINO_R1;
int relay2=CONTROLLINO_R2;
int relay3=CONTROLLINO_R3;
static char msgdata[PC_MSG_MAXLENGTH];
int pulseDuration = 1000;
int out = 0;
int fly = 0;

String msg = "";
int x = 0;
int msglen=0;
int msgerrorcount = 0;
static char jsondata[512];


void performActions(String action)
{
  
  //Normally I'd advise against using delays but in this context it may be beneficial to block serial comms until the actions are complete.
  
  if (action.equals("straight"))
  { 
    digitalWrite(relay0, HIGH);
    delay(pulseDuration); 
    digitalWrite(relay0, LOW);
  }

  else if(action.equals("left"))
  { 
    digitalWrite(relay1, HIGH);
    digitalWrite(relay2, HIGH);
    digitalWrite(relay3, HIGH);
    delay(pulseDuration);
    digitalWrite(relay1, LOW);
    digitalWrite(relay2, LOW);
    digitalWrite(relay3, LOW);
  }

  else if(action.equals("right"))
  {
    digitalWrite(relay1, HIGH);
    digitalWrite(relay2, HIGH);
    digitalWrite(relay3, HIGH);
    delay(pulseDuration);
    digitalWrite(relay1, LOW);
    digitalWrite(relay2, LOW);
    digitalWrite(relay3, LOW);
  }  

  else if(action.equals("wait"))
  {
    //do nothing.
  }
}

void checkSensors()
{
  out = digitalRead(capSensor);
  if(out==HIGH)
  {
    digitalWrite(synchPin, HIGH);
    debugln("Fly detected");
    debug("fly: ");
    debugln(fly);
    fly = 1;
    debugln(fly);
  }
  else 
  {
    digitalWrite(synchPin, LOW);
    fly = 0;
  }
}

void setup() {
    
    pinMode(capSensor, INPUT);
    pinMode(synchPin, OUTPUT);
    pinMode(relay0, OUTPUT);
    pinMode(relay1, OUTPUT);
    pinMode(relay2, OUTPUT);
    pinMode(relay3, OUTPUT);
    
    Serial.begin(SERIALSPEED);
    while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
    }
    if (DEBUG) {
      Serial2.begin(SERIALSPEED);
      while (!Serial2) {
      ; // wait for serial port to connect. Needed for native USB port only
      }
    }
    debug("Started");
}

void sendReply(StaticJsonDocument<PC_MSG_MAXLENGTH> msgDoc) {
  debugln("reply being processed");
  size_t s;
  jsondata[s] = 0;
  StaticJsonDocument<128> msgreply;
  msgreply["id"] = msgDoc["id"];
  msgreply["count"] = msgDoc["count"];
  s = serializeJson(msgreply, jsondata, 512);
  jsondata[s] = 0;
  Serial.write(jsondata, s + 1);
}

void loop()
{
  int av = Serial.available();
  bool msgerror = false;

  for (int i = 0; i < av; i++)
  {
    Serial.readBytes(&msgdata[msglen], 1);
    if (msgdata[msglen] == 0)
    {

      StaticJsonDocument<PC_MSG_MAXLENGTH> msgDoc;
      if (deserializeJson(msgDoc, msgdata, msglen) == DeserializationError::Ok)
      {
        sendReply(msgDoc);
        String msid = msgDoc["id"];
        debug("msg id received: ");
        debugln(msid);
        if(msid == NULL) {
          msgerror = true;
          debugln("msg ID is null");
        }
        else if (msid == "fire") {
          performActions(msgDoc["action"]);
          
        }
        else if (msid == "all lights on") {
          ;
        }
        else if (msid == "funnel on") {
          ;
        }
        else if (msid == "pups light on") {
          ;
        }
        else if (msid == "tunnel light on") {
          ;
        }
        else if (msid == "tunnel on") {
          ;
        }

      }

      else
      {
        debugln("error decoding");
        /*set the error flag*/
        msgerror = true;
      }
      /*clear the message array for next message*/
      msglen = 0;
      memset(msgdata, 1, sizeof(msgdata));
    }

    else if (msglen == PC_MSG_MAXLENGTH - 1)
    {
      debugln("pc msg too long");
      /*set the error flag*/
      msgerror = true;
    }
    else
    {
      msglen++;
      debug("msglen is: ");
      debugln(msglen);
      debug("byte read is: ");
      debugln(msgdata[msglen-1]);
    }

    /*if we detect an error, flush the serial buffer clear msg data and break*/
    if (msgerror == true)
    {
      /*clear the message array for next message*/
      msglen = 0;
      memset(msgdata, 1, sizeof(msgdata));
      /*read from the serial device until it is empty (returns -1)*/
      while (Serial.read() != -1)
        ;
      
      break;
    }
  }
  checkSensors();
}