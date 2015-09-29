class Token {
  constructor(value, type) {
    this.value = value;
    this.count = 1;
    this.type = type;
    this.possible = new Set();
    this.activeTag = null;
  }

  // Increase the count of this token
  // Also changes the type based on precedence file > extension > path
  increment(type) {
    this.count += 1;

    // If this type is of higher precedence
    if (type > this.type) {
      this.type = type;
    }
  }

  isActive() {
    return this.activeTag !== null;
  }

  setActive(tag) {
    this.activeTag = tag;
  }

}

// Static properties for enum like behaviour
Token.TYPEFILE = 2;
Token.TYPEEXT = 1;
Token.TYPEPATH = 0;

export default Token;
