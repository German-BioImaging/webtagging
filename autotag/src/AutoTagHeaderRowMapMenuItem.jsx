import React from 'react';

export default class AutoTagHeaderRowMapMenuItem extends React.Component {

  constructor() {
    super();

    // Prebind this to callback methods
    this.selectMapping = this.selectMapping.bind(this);
  }

  selectMapping() {
    this.props.selectMapping(this.props.token, this.props.tag);
  }

  render() {

    let content = this.props.textValue;
    if (this.props.tag !== null) {
      content += " (" + this.props.tag.id + ")";
    }
    return (
      <li onClick={this.selectMapping}>
        <a className={'tag-select'}>{content}</a>
      </li>
    );
  }
}
