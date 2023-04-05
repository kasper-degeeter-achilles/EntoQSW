#include <Controllino.h> /* Usage of CONTROLLINO library allows you to use CONTROLLINO_xx aliases in your sketch.*/ 


int capSensor=CONTROLLINO_I16;
int synchPin=CONTROLLINO_D0;
int relay0=CONTROLLINO_R0;
int relay1=CONTROLLINO_R1;
int relay2=CONTROLLINO_R2;
int relay3=CONTROLLINO_R3;


String msg = "";
int x = 0;

void setup() {
    
    pinMode(capSensor, INPUT);
    pinMode(synchPin, OUTPUT);
    pinMode(relay0, OUTPUT);
    pinMode(relay1, OUTPUT);
    pinMode(relay2, OUTPUT);
    pinMode(relay3, OUTPUT);
    Serial.begin(115200);

}


// the loop routine runs over and over again forever:
void loop()
{
  if (Serial.available()>0) {
    msg=Serial.readStringUntil("\n");
    int msglen=msg.length()+1; 
    char charstring[msglen];
    msg.toCharArray(charstring, msglen);
    x = atoi(charstring);
    Serial.println(String(x)); //send acknowledge
  }
  if (x == 10) { /*Rechtdoor; rare getallen om schakelen relais bij nog op te sporen bug te vermijden*/
    digitalWrite(relay0, LOW);
    delay(2000);
    digitalWrite(relay0, HIGH);
  }
  else if (x == 11) { /*Links*/
    digitalWrite(relay1, LOW);
    digitalWrite(relay2, LOW);
    digitalWrite(relay3, LOW);
    delay(2000);
    digitalWrite(relay1, HIGH);
    digitalWrite(relay2, HIGH);
    digitalWrite(relay3, HIGH);
    
  }
  else if (x == 12) { /*Rechts*/
    digitalWrite(relay1, LOW);
    digitalWrite(relay2, LOW);
    digitalWrite(relay3, LOW);
    delay(2000);
    digitalWrite(relay1, HIGH);
    digitalWrite(relay2, HIGH);
    digitalWrite(relay3, HIGH);
  }  
  
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
