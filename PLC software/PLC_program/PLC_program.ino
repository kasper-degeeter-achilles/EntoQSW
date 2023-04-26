#include <Controllino.h> /* Usage of CONTROLLINO library allows you to use CONTROLLINO_xx aliases in your sketch.*/ 
#include <ArduinoJson.h>

#define PC_MSG_MAXLENGTH 256

int capSensor=CONTROLLINO_I16;
int synchPin=CONTROLLINO_D0;
int relay0=CONTROLLINO_R0;
int relay1=CONTROLLINO_R1;
int relay2=CONTROLLINO_R2;
int relay3=CONTROLLINO_R3;
static char msgdata[PC_MSG_MAXLENGTH];
int pulseDuration = 1000;

String msg = "";
int x = 0;
int msglen=0;

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
  if(digitalRead(capSensor)==HIGH)
  {
    //Serial.println("Fly detected");
    digitalWrite(synchPin, HIGH);
  }
  else 
  {
    //Serial.println("No fly detected");
    digitalWrite(synchPin, LOW);
  }
}

void setup() {
    
    pinMode(capSensor, INPUT);
    pinMode(synchPin, OUTPUT);
    pinMode(relay0, OUTPUT);
    pinMode(relay1, OUTPUT);
    pinMode(relay2, OUTPUT);
    pinMode(relay3, OUTPUT);
    Serial.begin(115200);
    delay(1000);
    Serial.println("Started");
}


// the loop routine runs over and over again forever:
void loop()
{
  int av = Serial.available();
  for (int i = 0; i < av; i++)
  {
    Serial.println("Read a byte");
    Serial.readBytes(&msgdata[msglen], 1);
    if (msgdata[msglen] == 0)
    {
      Serial.println("Decoding json");
      StaticJsonDocument<PC_MSG_MAXLENGTH> msgDoc;
      if (deserializeJson(msgDoc, msgdata, msglen) == DeserializationError::Ok)
      {
        String action=msgDoc["action"];
        performActions(action);
      }
      else
      {
        Serial.println("Message ungood");
      }
      msglen = 0;
      memset(msgdata, 1, sizeof(msgdata));
    }
    else if (msglen == PC_MSG_MAXLENGTH - 1)
    {
      Serial.println("Message too long");
      //Log.warningln("pc msg too long");
      msglen=0;
    }
    else
    {
      msglen++;
    }
  }

  checkSensors();
}
