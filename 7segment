// file: binary_addition_display_5461AS.ino
  // Performs binary addition (A+B) and displays the 4 least significant bits
  // on a 5461AS 4-digit seven-segment display
  // e.g. input "1010+0111" -> sum=10001 -> display "0001"

  #include <SevSeg.h>
  SevSeg sevseg;

  String inputString = "";
  bool stringComplete = false;

  // Display modes
  enum DisplayMode { MODE_DEC = 0, MODE_OCT = 1, MODE_HEX = 2 };
  DisplayMode displayMode = MODE_DEC;

  // Remember last computed integer result
  long lastResult = 0;
  // Remember last computed floating result for decimal display
  double lastFloat = 0.0;
  bool lastHasFraction = false;
  uint8_t lastDecPlaces = 0; // for logging only
  // Remember last 4-character display content
  char lastDisplay[5] = "0000";

  // Function to convert hex string to decimal
  int hexToDec(String hex) {
      return strtol(hex.c_str(), NULL, 16);
  }

  // Function to convert octal string to decimal
  int octToDec(String oct) {
      return strtol(oct.c_str(), NULL, 8);
  }

  // Function to perform addition
  String add(String a, String b, int base) {
      int num1 = (base == 16) ? hexToDec(a) : octToDec(a);
      int num2 = (base == 16) ? hexToDec(b) : octToDec(b);
      return String(num1 + num2);
  }

  // Function to perform multiplication
  String multiply(String a, String b, int base) {
      int num1 = (base == 16) ? hexToDec(a) : octToDec(a);
      int num2 = (base == 16) ? hexToDec(b) : octToDec(b);
      return String(num1 * num2);
  }

  // Function to perform binary addition
  String addBinary(String a, String b) {
      return add(a, b, 2);
  }

  // Function to perform binary multiplication
  String multiplyBinary(String a, String b) {
      return multiply(a, b, 2);
  }

  void displayConversions(String binary) {
      int decimal = strtol(binary.c_str(), NULL, 2);
      String octal = String(decimal, 8);
      String hex = String(decimal, 16);
      Serial.print("Binary: "); Serial.println(binary);
      Serial.print("Decimal: "); Serial.println(decimal);
      Serial.print("Octal: "); Serial.println(octal);
      Serial.print("Hexadecimal: "); Serial.println(hex);
  }

  bool isValidDigits(const String &s, int base) {
    if (s.length() == 0) return false;
    int dots = 0;
    for (unsigned int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      if (c == '.') {
        dots++;
        if (dots > 1) return false;
        continue;
      }
      if (base == 2) {
        if (c != '0' && c != '1') return false;
      } else if (base == 8) {
        if (c < '0' || c > '7') return false;
      } else { // base 16
        if (!((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F'))) return false;
      }
    }
    return true;
  }

  int digitToVal(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return 10 + (c - 'A');
    if (c >= 'a' && c <= 'f') return 10 + (c - 'a');
    return -1;
  }

  double parseToDouble(const String &sIn, int base) {
    String s = sIn; s.trim();
    int dotPos = s.indexOf('.');
    String si = (dotPos >= 0) ? s.substring(0, dotPos) : s;
    String sf = (dotPos >= 0) ? s.substring(dotPos + 1) : "";
    si.trim(); sf.trim();
    // integer part
    long iv = strtol(si.c_str(), NULL, base);
    double fv = 0.0;
    double denom = (double) base;
    for (unsigned int i = 0; i < sf.length(); i++) {
      char c = sf.charAt(i);
      int v = digitToVal(c);
      if (v < 0 || v >= base) break;
      fv += ((double)v) / denom;
      denom *= (double) base;
    }
    if (iv >= 0) return ((double)iv) + fv; else return ((double)iv) - fv;
  }

  void updateDisplay() {
    // Ensure non-negative for display
    unsigned long ival = (lastResult < 0) ? 0 : (unsigned long) lastResult;
    if (displayMode == MODE_DEC) {
      // Choose decimal places to fit 4 digits
      double v = lastHasFraction ? fabs(lastFloat) : (double)ival;
      uint8_t places = 0;
      if (v >= 1000.0) places = 0;         // 1234
      else if (v >= 100.0) places = 1;     // 123.4
      else if (v >= 10.0) places = 2;      // 12.34
      else places = 3;                     // 1.234 or 0.123
      lastDecPlaces = places;
      sevseg.setNumberF(v, places, false);
      // Update lastDisplay for logging with just the digits (no dot)
      unsigned long scaled = (unsigned long)(v * (places == 0 ? 1 : (places == 1 ? 10 : (places == 2 ? 100 : 1000))) + 0.5);
      // Extract last 4 digits after scaling
      char buf[5];
      sprintf(buf, "%04lu", scaled % 10000UL);
      memcpy(lastDisplay, buf, 5);
    } else if (displayMode == MODE_OCT) {
      String s = String(ival, 8); // octal
      while (s.length() < 4) s = "0" + s;
      if (s.length() > 4) s = s.substring(s.length() - 4);
      s.toUpperCase();
      s.toCharArray(lastDisplay, 5);
      sevseg.setChars(lastDisplay);
    } else { // MODE_HEX
      String s = String(ival, 16); // hex
      s.toUpperCase();
      while (s.length() < 4) s = "0" + s;
      if (s.length() > 4) s = s.substring(s.length() - 4);
      s.toCharArray(lastDisplay, 5);
      sevseg.setChars(lastDisplay);
    }
  }

  void setup() {
    Serial.begin(9600);
    Serial.println("Binary Addition Display System Ready (4-bit output)");

    byte numDigits = 4;
    byte digitPins[]   = {13, 12, 11, 10};               // D1..D4 (left->right)
    byte segmentPins[] = {2, 3, 4, 5 ,6 ,7 ,8 ,9};       // A,B,C,D,E,F,G,DP
    bool resistorsOnSegments = true;
    byte hardwareConfig = COMMON_CATHODE; // change to COMMON_ANODE if needed

    sevseg.begin(hardwareConfig, numDigits, digitPins, segmentPins, resistorsOnSegments);
    sevseg.setBrightness(90);
  // Display 0000 at startup
  strcpy(lastDisplay, "0000");
  sevseg.setChars(lastDisplay);
  }

  void loop() {
    sevseg.refreshDisplay();

    if (stringComplete) {
      stringComplete = false;
      inputString.trim();

      // Allow mode switching commands: DEC, OCT, HEX
      String upper = inputString;
      upper.toUpperCase();
      if (upper == "DEC") {
        displayMode = MODE_DEC;
        updateDisplay();
        Serial.println("Mode set: DEC");
        inputString = "";
        return;
      } else if (upper == "OCT") {
        displayMode = MODE_OCT;
        updateDisplay();
        Serial.println("Mode set: OCT");
        inputString = "";
        return;
      } else if (upper == "HEX") {
        displayMode = MODE_HEX;
        updateDisplay();
        Serial.println("Mode set: HEX");
        inputString = "";
        return;
      } else if (upper.startsWith("SET ") || upper.startsWith("SET=")) {
        // Accept: SET <decimal> or SET=<decimal>
        int sep = inputString.indexOf(' ');
        if (sep < 0) sep = inputString.indexOf('=');
        String num = (sep >= 0) ? inputString.substring(sep + 1) : "";
        num.trim();
        if (num.length() == 0) {
          Serial.println("ERR: SET requires a number, e.g. 'SET 1234'");
        } else {
          double dv = strtod(num.c_str(), NULL);
          long val = (dv >= 0) ? (long)(dv + 0.5) : (long)(dv - 0.5);
          lastResult = val;
          lastFloat = dv;
          lastHasFraction = (num.indexOf('.') >= 0);
          updateDisplay();
          Serial.print("SET -> "); Serial.println(dv, 4);
        }
        inputString = "";
        return;
      }

      // Accept formats like:
      //   BIN:1010+0111
      //   OCT:17-3
      //   HEX:1A*0F
      //   1010/10              (defaults to BIN)
      int base = 2; // default
      String expr = inputString;
      String uexpr = expr; uexpr.toUpperCase();
      if (uexpr.startsWith("BIN:")) {
        base = 2; expr = expr.substring(4);
      } else if (uexpr.startsWith("OCT:")) {
        base = 8; expr = expr.substring(4);
      } else if (uexpr.startsWith("HEX:")) {
        base = 16; expr = expr.substring(4);
      }

      // Find operator among + - * /
      int opIndex = -1; char op = 0;
      const char ops[4] = {'+', '-', '*', '/'};
      for (int i = 0; i < 4; i++) {
        int idx = expr.indexOf(ops[i]);
        if (idx > 0) { opIndex = idx; op = ops[i]; break; }
      }
      if (opIndex < 1 || op == 0) {
        Serial.println("ERR: Invalid format. Use e.g. BIN:1010+0111, OCT:17-3, HEX:1A*0F, or 1010/10");
        inputString = "";
        return;
      }

      String a_str = expr.substring(0, opIndex);
      String b_str = expr.substring(opIndex + 1);
      a_str.trim(); b_str.trim();
      a_str.toUpperCase(); b_str.toUpperCase();

      if (!isValidDigits(a_str, base) || !isValidDigits(b_str, base)) {
        Serial.println("ERR: Digit out of range for selected base.");
        inputString = "";
        return;
      }

      // convert to doubles for given base (support fractional)
      double a_val = parseToDouble(a_str, base);
      double b_val = parseToDouble(b_str, base);
      double res = 0.0;
      if (op == '+') res = a_val + b_val;
      else if (op == '-') res = a_val - b_val;
      else if (op == '*') res = a_val * b_val;
      else {
        if (b_val == 0.0) {
          Serial.println("ERR: Division by zero");
          inputString = "";
          return;
        }
        res = a_val / b_val;
      }
      long result_val = (res >= 0.0) ? (long)(res + 0.5) : (long)(res - 0.5);

      // Store and display according to current mode
      lastResult = result_val;
      lastFloat = res;
      lastHasFraction = (fabs(res - (double)result_val) > 0.0005);
      updateDisplay();

      Serial.print("A:"); Serial.print(a_str);
      Serial.print(" ("); Serial.print(a_val, 4);
      Serial.print(")  B:"); Serial.print(b_str);
      Serial.print(" ("); Serial.print(b_val, 4);
      Serial.print(")  ");
      const char* lbl = (op == '+') ? "SUM:" : (op == '-') ? "DIFF:" : (op == '*') ? "PRODUCT:" : "QUOTIENT:";
      Serial.print(lbl);
      Serial.print(res, 4);
      // Log what will be shown
      Serial.print("  Display: ");
      if (displayMode == MODE_DEC && lastDecPlaces > 0) {
        // Insert decimal point for logging
        // Determine position from right based on places
        char logbuf[8]; // enough for 4 digits + dot + null
        uint8_t p = lastDecPlaces;
        // Copy lastDisplay digits and add dot before the last p digits
        int li = 0;
        for (int i = 0; i < 4; i++) {
          if (4 - i == p && p > 0) logbuf[li++] = '.';
          logbuf[li++] = lastDisplay[i];
        }
        logbuf[li] = '\0';
        Serial.println(logbuf);
      } else {
        Serial.println(lastDisplay);
      }

      inputString = "";
    }
  }


  void serialEvent() {
    while (Serial.available()) {
      char inChar = (char)Serial.read();
      if (inChar == '\n' || inChar == '\r') {
        if (inputString.length() > 0) stringComplete = true;
      } else {
        inputString += inChar;
      }
    }
  }
